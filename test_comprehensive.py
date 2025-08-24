#!/usr/bin/env python3
"""Comprehensive test of Blueprint template functionality."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, '.')

# Add airflow stub to path 
sys.modules['airflow'] = __import__('airflow_stub')
sys.modules['airflow.operators'] = type(sys)('airflow.operators')
sys.modules['airflow.operators.bash'] = type(sys)('airflow.operators.bash')
sys.modules['airflow.operators.python'] = type(sys)('airflow.operators.python')
sys.modules['airflow.operators.bash'].BashOperator = sys.modules['airflow'].BashOperator
sys.modules['airflow.operators.python'].PythonOperator = sys.modules['airflow'].PythonOperator

sys.path.insert(0, 'examples/.astro/templates')

def test_runtime_generation():
    """Test runtime DAG generation from YAML."""
    print("🔬 Testing runtime DAG generation...")
    
    from blueprint.template_loader import discover_yaml_dags
    
    dags = discover_yaml_dags(
        configs_dir='examples/dags/configs',
        template_dir='examples/.astro/templates'
    )
    
    assert len(dags) == 2, f"Expected 2 DAGs, got {len(dags)}"
    assert 'customer_etl' in dags, "customer_etl DAG not found"
    assert 'sales_analytics' in dags, "sales_analytics DAG not found"
    
    print("  ✅ Runtime generation works")
    return True

def test_template_generation():
    """Test template code generation."""
    print("🔬 Testing template code generation...")
    
    from daily_etl import DailyETL, DailyETLConfig
    
    blueprint = DailyETL()
    config = DailyETLConfig(
        job_id='test-template-dag',
        source_table='raw.test',
        target_table='analytics.test',
        schedule='@hourly',
        retries=1
    )
    
    template_code = blueprint.render_template(config)
    
    # Verify template contains expected elements
    assert 'test-template-dag' in template_code, "DAG ID not in template"
    assert 'raw.test' in template_code, "Source table not in template"
    assert 'analytics.test' in template_code, "Target table not in template"
    assert '@hourly' in template_code, "Schedule not in template"
    assert 'from airflow import DAG' in template_code, "Import not in template"
    
    print("  ✅ Template generation works")
    return True

def test_build_command():
    """Test CLI build command."""
    print("🔬 Testing CLI build command...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        import subprocess
        result = subprocess.run([
            sys.executable, '-m', 'blueprint.cli', 'build',
            '--config-dir', 'examples/dags/configs',
            '--output-dir', temp_dir,
            '--template-dir', 'examples/.astro/templates',
            '--force'
        ], capture_output=True, text=True, cwd='.')
        
        assert result.returncode == 0, f"Build command failed: {result.stderr}"
        
        # Check that files were created
        output_path = Path(temp_dir)
        dag_files = list(output_path.glob('*.py'))
        assert len(dag_files) == 2, f"Expected 2 DAG files, got {len(dag_files)}"
        
        # Check file contents
        customer_etl_file = output_path / 'customer_etl.py'
        assert customer_etl_file.exists(), "customer_etl.py not created"
        
        content = customer_etl_file.read_text()
        assert 'customer-daily-sync' in content, "DAG ID not in generated file"
        assert 'from airflow import DAG' in content, "Import not in generated file"
        
    print("  ✅ CLI build command works")
    return True

def test_backward_compatibility():
    """Test that existing functionality still works."""
    print("🔬 Testing backward compatibility...")
    
    from daily_etl import DailyETL
    
    # Test that build method exists and works
    dag = DailyETL.build(
        job_id='compat-test',
        source_table='raw.compat',
        target_table='analytics.compat'
    )
    
    assert dag.dag_id == 'compat-test', f"Expected DAG ID 'compat-test', got {dag.dag_id}"
    
    print("  ✅ Backward compatibility maintained")
    return True

if __name__ == '__main__':
    print("🚀 Running comprehensive Blueprint template tests...\n")
    
    try:
        test_runtime_generation()
        test_template_generation() 
        test_build_command()
        test_backward_compatibility()
        
        print("\n🎉 All tests passed! Blueprint template functionality is working correctly.")
        print("\n📝 Summary of functionality:")
        print("  ✅ Runtime DAG generation from YAML (existing functionality)")
        print("  ✅ Build-time DAG file generation (new functionality)")
        print("  ✅ CLI build command (new functionality)")
        print("  ✅ Template code generation (new functionality)")
        print("  ✅ Backward compatibility maintained")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)