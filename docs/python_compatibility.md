# Python Version Compatibility Analysis

## Type Annotations We're Using

### 1. Union Types with `|` syntax
```python
optional_param: str | None = None
```
**Requires:** Python 3.10+
**Alternative for older versions:**
```python
from typing import Union
optional_param: Union[str, None] = None
# or
optional_param: Optional[str] = None
```

### 2. Generic Classes
```python
from typing import Generic, TypeVar
T = TypeVar('T', bound=TypedDict)

class Blueprint(Generic[T]):
    ...
```
**Requires:** Python 3.5+ (typing module)
**Widely supported**

### 3. TypedDict
```python
from typing import TypedDict

class MyConfig(TypedDict):
    param: str
```
**Requires:** Python 3.8+ (or `typing_extensions` for 3.6-3.7)

### 4. TypedDict with `total=False`
```python
class MyConfig(TypedDict, total=False):
    optional_field: str
```
**Requires:** Python 3.8+

### 5. Annotated (for parameter descriptions)
```python
from typing import Annotated
param: Annotated[str, "Description"]
```
**Requires:** Python 3.9+ (or `typing_extensions` for 3.6-3.8)

## Airflow Python Support

| Airflow Version | Python Support |
|-----------------|----------------|
| 2.8.x (current) | 3.8, 3.9, 3.10, 3.11 |
| 2.7.x | 3.8, 3.9, 3.10, 3.11 |
| 2.6.x | 3.8, 3.9, 3.10, 3.11 |

**Note:** Airflow dropped Python 3.7 support in version 2.5.0

## Recommended Approach

### Option 1: Target Python 3.8+ (Conservative)
```python
from typing import TypedDict, Generic, TypeVar, Union, Optional
from typing_extensions import Annotated  # Backport for 3.8

# Use Union instead of |
optional_param: Union[str, None] = None
# or
optional_param: Optional[str] = None

# Rest works fine
class MyConfig(TypedDict):
    param: str

class Blueprint(Generic[T]):
    ...
```

### Option 2: Target Python 3.10+ (Modern)
```python
from typing import TypedDict, Generic, TypeVar, Annotated

# Use modern union syntax
optional_param: str | None = None

# All features work natively
```

### Option 3: Conditional Imports (Flexible)
```python
import sys
from typing import TypedDict, Generic, TypeVar, Union

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

if sys.version_info >= (3, 10):
    # Use | syntax in string annotations only
    pass
else:
    # Use Union
    pass
```

## Recommendations

**For Blueprint package:**

1. **Target Python 3.8+** to align with Airflow support
2. **Use `typing_extensions` for backports** when needed
3. **Avoid `|` union syntax** - use `Union` or `Optional` 
4. **Use string annotations** for forward references
5. **Add runtime checks** for Python version if using newer features

**pyproject.toml:**
```toml
[project]
requires-python = ">=3.8"
dependencies = [
    "typing-extensions>=4.0.0; python_version<'3.9'",
]
```

**Updated examples:**
```python
from typing import TypedDict, Generic, TypeVar, Union, Optional
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

class MyConfig(TypedDict):
    required_param: str
    optional_param: Optional[str]  # Instead of str | None
    
class Blueprint(Generic[T]):
    def render(self, config: T) -> 'DAG':  # String annotation for forward ref
        ...
```

This ensures compatibility with all currently supported Airflow versions while maintaining modern type safety.