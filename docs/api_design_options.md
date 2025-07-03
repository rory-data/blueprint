# Blueprint API Design Options

## Option 1: Current Approach - Decorator + Class
```python
@blueprint(name="daily_etl")
class DailyETL:
    config: DailyETLConfig
    def render(self, config: DailyETLConfig) -> DAG:
        ...
```

**Pros:**
- Explicit registration via decorator
- Name separate from class name (flexibility)
- Familiar pattern (Flask routes, FastAPI endpoints)

**Cons:**
- Two places to look (decorator + class)
- Not immediately clear what makes a class a blueprint

## Option 2: Class Inheritance
```python
class DailyETL(Blueprint):
    name = "daily_etl"
    config_type = DailyETLConfig  # or as type annotation
    
    def render(self, config: DailyETLConfig) -> DAG:
        ...
```

**Pros:**
- Standard OOP pattern
- Single source - everything in the class
- `isinstance(obj, Blueprint)` works
- Clear what is a blueprint

**Cons:**
- Inheritance can be limiting
- Name as class attribute feels less natural

## Option 3: Generic Base Class
```python
from typing import Generic, TypeVar

T = TypeVar('T', bound=BlueprintConfig)

class DailyETL(Blueprint[DailyETLConfig]):
    name = "daily_etl"
    
    def render(self, config: DailyETLConfig) -> DAG:
        ...
```

**Pros:**
- Type safety built into inheritance
- Modern Python pattern
- IDE understands config type automatically

**Cons:**
- More complex for users unfamiliar with generics
- Still need name attribute

## Option 4: Convention-based (like Django)
```python
# blueprints.py or in .astro/templates/
class DailyETLBlueprint:  # Must end with "Blueprint"
    config: DailyETLConfig
    
    def render(self, config: DailyETLConfig) -> DAG:
        ...
```

**Pros:**
- No decorator or base class needed
- Simple and clean
- Name derived from class name

**Cons:**
- "Magic" discovery based on naming
- Less explicit
- Harder to have different name than class

## Option 5: Functional Approach
```python
@blueprint(name="daily_etl", config=DailyETLConfig)
def render_daily_etl(config: DailyETLConfig) -> DAG:
    with DAG(...) as dag:
        ...
    return dag
```

**Pros:**
- Simple for basic blueprints
- No class needed
- Very explicit

**Cons:**
- No place for helper methods
- Less organized for complex blueprints

## Option 6: Registry Pattern
```python
from blueprint import BlueprintRegistry

class DailyETL:
    config: DailyETLConfig
    
    def render(self, config: DailyETLConfig) -> DAG:
        ...

# Explicit registration
BlueprintRegistry.register("daily_etl", DailyETL)
```

**Pros:**
- Very explicit
- Separates definition from registration
- Could register same class multiple times

**Cons:**
- Extra step required
- Registration could be forgotten

## Recommendation

I lean towards **Option 2 (Class Inheritance)** or **Option 3 (Generic Base)** because:

1. It's the most standard Python pattern
2. Makes it immediately clear what is a blueprint
3. Provides a natural place for shared functionality
4. Works well with type checkers and IDEs

The generic approach would look like:

```python
from blueprint import Blueprint
from typing import Generic, TypeVar

T = TypeVar('T', bound=BlueprintConfig)

class Blueprint(Generic[T]):
    # Name can be inferred from class name or overridden
    name: str | None = None
    
    def get_name(self) -> str:
        if self.name:
            return self.name
        # Convert "DailyETLBlueprint" -> "daily_etl"
        name = self.__class__.__name__
        if name.endswith("Blueprint"):
            name = name[:-9]
        # Convert CamelCase to snake_case
        return to_snake_case(name)
    
    def render(self, config: T) -> DAG:
        raise NotImplementedError

# Usage - clean and simple
class DailyETL(Blueprint[DailyETLConfig]):
    def render(self, config: DailyETLConfig) -> DAG:
        ...

# Or with explicit name
class CustomerSync(Blueprint[CustomerSyncConfig]):
    name = "customer_etl"  # Override auto-generated name
    
    def render(self, config: CustomerSyncConfig) -> DAG:
        ...
```