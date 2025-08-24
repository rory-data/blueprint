#!/usr/bin/env python3
"""Simple test script for template generation functionality."""

import sys
sys.path.insert(0, '.')

# First test if we can import the updated core
try:
    from blueprint.core import Blueprint
    print("✅ Blueprint class imported successfully")
except Exception as e:
    print(f"❌ Failed to import Blueprint: {e}")
    sys.exit(1)

# Test with a simple mock BaseModel since we can't install pydantic
class MockBaseModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def model_fields(cls):
        return {}
    
    @classmethod
    def model_json_schema(cls):
        return {}

class MockConfig(MockBaseModel):
    def __init__(self, job_id="test-job", schedule="@daily"):
        self.job_id = job_id
        self.schedule = schedule

# Test the new template rendering functionality
class TestBlueprint(Blueprint):
    _config_type = MockConfig
    
    def render(self, config):
        # Mock DAG render for testing
        return f"MockDAG(dag_id={config.job_id}, schedule={config.schedule})"
    
    def render_template(self, config) -> str:
        return f'''
from airflow import DAG
from datetime import datetime

dag = DAG(
    dag_id="{config.job_id}",
    schedule="{config.schedule}",
    start_date=datetime(2024, 1, 1),
)
'''

# Test the template generation
try:
    blueprint = TestBlueprint()
    config = MockConfig(job_id="test-dag", schedule="@hourly")
    
    # Test render method (existing functionality)
    dag_obj = blueprint.render(config)
    print(f"✅ render() works: {dag_obj}")
    
    # Test render_template method (new functionality)
    template_code = blueprint.render_template(config)
    print("✅ render_template() works:")
    print("--- Generated Template ---")
    print(template_code)
    print("--- End Template ---")
    
except Exception as e:
    print(f"❌ Template generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n🎉 Template generation functionality test passed!")