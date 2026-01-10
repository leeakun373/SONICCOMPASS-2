# Super-Anchor Strategy Implementation

**Last Updated**: 2025-01-10  
**Status**: ⚠️ **In Progress** - Strategy implemented but drift issue not fully resolved  
**Related**: UMAP Coordinate Calculation, Main Category Clustering

## Overview

This document describes the implementation of the **Super-Anchor Strategy** to address the "Continental Drift" problem in UMAP visualization, where subcategories from the same main category (e.g., `ANMLMisc`) "drift away" to other continents despite being correctly classified.

## Problem Statement: Continental Drift

### Symptoms

During UMAP visualization, some subcategories that belong to the same main category (e.g., `ANIMALS`) appear in incorrect "continents" (clusters). For example:

- **Example Case**: `ANMLMisc` (Miscellaneous Animals) subcategory with file `Asian Palm Civet` (果子狸)
- **Expected Location**: Should be in the `ANIMALS` continent
- **Actual Location**: Appears near `ANMLWcat` (Lion) files in a different position, far from its subcategory siblings (e.g., Camel)
- **Root Cause**: UMAP is an "honest" algorithm - it prioritizes high-dimensional feature similarity over classification labels. When audio features (e.g., growl sounds) are more similar between different subcategories than within the same subcategory, UMAP chooses acoustic similarity over categorical correctness.

### Evidence

Analysis of CSV output files (`verify_ALL_details_*.csv`) revealed:
- Asian Palm Civet at position `(X=6.65, Y=5.28)` 
- Camel (same subcategory) at position `(X=7.73, Y=4.60)` - **far apart**
- Lion (different subcategory) at position `(X=6.64, Y=5.23)` - **adjacent to Asian Palm Civet**

This confirms that UMAP is clustering by **acoustic similarity** (growl sounds) rather than **categorical membership** (both are animals).

## Solution: Super-Anchor Strategy

### Concept

Instead of relying solely on UMAP's supervised learning with `target_weight` (which is not strong enough), we inject **One-Hot vectors** of main categories directly into the embedding space. This creates "gravitational anchors" that force same-category data to cluster together.

### Implementation

#### Architecture (DRY Principle)

The core function is implemented in `core/data_processor.py` as a module-level function:

```python
def inject_category_vectors(
    embeddings: np.ndarray,
    target_labels: List[str],
    audio_weight: float = 1.0,
    category_weight: float = 15.0
) -> Tuple[np.ndarray, OneHotEncoder]:
```

**Key Design Decisions**:
1. **DRY Principle**: Single implementation shared across all scripts
2. **String Lists Only**: Accepts original string labels (e.g., `["ANIMALS", "WEAPONS"]`) to avoid `-1` trap with OneHotEncoder
3. **Weight Tuning**: `category_weight=15.0` provides strong "glue" to keep categories together

#### Vector Injection Process

1. **Input**: Audio embeddings `(N, 1024)` + Main category labels `(N,)` as strings
2. **One-Hot Encoding**: Convert category labels to One-Hot vectors `(N, num_categories)`
3. **Weight Application**: 
   - Audio features: `embeddings * 1.0`
   - Category vectors: `one_hot_vectors * 15.0` (strong anchor)
4. **Concatenation**: `X_combined = [audio_features, category_vectors]` → `(N, 1024 + num_categories)`
5. **Output**: Mixed vector fed to UMAP instead of original embeddings

#### Modified Files

1. **`core/data_processor.py`**: Added `inject_category_vectors()` function
2. **`core/__init__.py`**: Exported function for use across modules
3. **`recalculate_umap.py`**: Applied strategy before UMAP calculation
4. **`rebuild_atlas.py`**: Applied strategy before UMAP calculation
5. **`tools/verify_subset.py`**: Applied strategy for verification consistency
6. **`ui/main_window.py`**: Applied strategy in 3 locations for UI consistency

#### Parameter Adjustments

All scripts now use consistent parameters:
- **`min_dist=0.05`**: Allows tighter clustering (reduced from 0.1)
- **`target_weight=0.5`**: Reduced from 0.95 since vector injection provides primary constraint
- **`category_weight=15.0`**: Strong "gravitational" force (may need tuning)

### Code Example

```python
# Extract main category labels as strings (not encoded integers)
targets_original = ["ANIMALS", "WEAPONS", "ANIMALS", "UNCATEGORIZED", ...]

# Apply Super-Anchor Strategy
from core import inject_category_vectors

X_combined, encoder = inject_category_vectors(
    embeddings=embeddings,
    target_labels=targets_original,  # Use string list, not encoded integers
    audio_weight=1.0,
    category_weight=15.0  # Strong gravitational anchor
)

# Use X_combined instead of original embeddings
reducer = umap.UMAP(
    n_components=2,
    min_dist=0.05,        # Tighter clustering
    target_weight=0.5,    # Reduced since injection is primary constraint
    target_metric='categorical',
    random_state=42
)

coords_2d = reducer.fit_transform(X_combined, y=targets_encoded)
```

## Current Status

### ✅ Implemented

- [x] Core `inject_category_vectors()` function in `core/data_processor.py`
- [x] Function exported in `core/__init__.py`
- [x] Strategy applied to `recalculate_umap.py`
- [x] Strategy applied to `rebuild_atlas.py`
- [x] Strategy applied to `tools/verify_subset.py` (with adaptive weighting)
- [x] Strategy applied to `ui/main_window.py` (3 locations for consistency)
- [x] All scripts use consistent parameters (`min_dist=0.05`, `target_weight=0.5`)

### ⚠️ Not Fully Resolved

**The continental drift issue persists after implementation.**

Initial testing with `tools/verify_subset.py --all` shows:
- Strategy is applied correctly (no errors)
- Vector injection occurs as expected
- However, subcategories may still drift if:
  1. `category_weight=15.0` is insufficient (may need 20.0-25.0)
  2. `min_dist=0.05` causes over-crowding, masking the issue
  3. The problem is more fundamental (UMAP's inherent behavior)

### Next Steps

1. **Parameter Tuning**: Test with higher `category_weight` values (20.0, 25.0, 30.0)
2. **Distance Adjustment**: Try `min_dist=0.1-0.2` if points are too crowded
3. **Validation**: Compare CSV outputs before/after to quantify improvement
4. **Alternative Approaches**: Consider grid snapping or topological constraints if vector injection proves insufficient

## Technical Notes

### Uncategorized Handling

- **Critical**: Must pass **string lists** (`["UNCATEGORIZED", ...]`) to `inject_category_vectors()`, not encoded integers (`[-1, ...]`)
- **Reason**: `OneHotEncoder` cannot handle negative integers
- **Implementation**: Save `targets_original = targets.copy()` before encoding to integers

### Performance Impact

- **Dimension Increase**: Embeddings grow from `(N, 1024)` to `(N, 1024 + num_categories)` ≈ `(N, 1106)`
- **Impact**: Negligible on UMAP performance (dimension still manageable)
- **Memory**: ~8% increase per embedding vector

### Algorithm Consistency

- **UI Synchronization**: All UMAP calculations (offline and real-time) use the same strategy
- **Benefit**: Prevents inconsistency when adding new files or using Gravity Mode
- **Locations**: 
  - `IndexBuilderThread.run()` (UI thread)
  - `AtlasBuilderThread.run()` (UI thread)
  - `_compute_umap_coordinates_sync()` (synchronous computation)

## References

- **UMAP Documentation**: [umap-learn documentation](https://umap-learn.readthedocs.io/)
- **Supervised UMAP**: Using `target_weight` and `target_metric='categorical'`
- **One-Hot Encoding**: `sklearn.preprocessing.OneHotEncoder`

## Related Files

- `core/data_processor.py` - Core implementation
- `recalculate_umap.py` - Offline coordinate recalculation
- `rebuild_atlas.py` - Full atlas reconstruction
- `tools/verify_subset.py` - Verification and testing tool
- `ui/main_window.py` - UI thread implementations

---

**Status Note**: This strategy represents a significant architectural improvement (DRY principle, consistent algorithm) but may require further parameter tuning or alternative approaches to fully resolve the continental drift issue. The foundation is solid, but the problem is complex.
