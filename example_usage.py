"""
Example usage of ZeroInboxAgent - Clean Python runner for email categorization
"""

from zero_inbox_runner import ZeroInboxAgent

def example_basic_usage():
    """Basic usage examples."""
    print("=== BASIC USAGE EXAMPLES ===\n")
    
    agent = ZeroInboxAgent()
    
    # 1. Simple full pipeline
    print("1. Full pipeline (setup + fetch + categorize)")
    results = agent.run()
    print(f"   Fetched: {results.get('fetch_emails', {}).get('fetched', 0)} emails")
    print(f"   Categorized: {results.get('categorize_emails', {}).get('processed', 0)} emails")
    
    # 2. Just get current stats
    print("\n2. Get current statistics")
    stats = agent.get_stats()
    print(f"   Total emails: {stats.get('total_emails', 0)}")
    print(f"   Categorized: {stats.get('categorized_emails', 0)}")
    print(f"   Rate: {stats.get('categorization_rate', 0):.1%}")


def example_custom_parameters():
    """Examples with custom parameters."""
    print("\n=== CUSTOM PARAMETERS ===\n")
    
    agent = ZeroInboxAgent()
    
    # 1. Setup only
    print("1. Setup only")
    setup_result = agent.run(['setup'])
    print(f"   Database ready: {setup_result['setup']['components_ready']}")
    
    # 2. Fetch with date range
    print("\n2. Fetch emails from specific date range")
    fetch_result = agent.run(
        ['fetch_emails'],
        fetch_emails={
            'from_date': '2025-08-28',
            'to_date': '2025-08-29',
            'max_emails': 10
        }
    )
    print(f"   Fetched: {fetch_result['fetch_emails'].get('fetched', 0)} emails")
    
    # 3. Categorize in larger batches
    print("\n3. Categorize with larger batch size")
    categorize_result = agent.run(
        ['categorize_emails'],
        categorize_emails={
            'batch_size': 10,
            'limit': 20
        }
    )
    print(f"   Processed: {categorize_result['categorize_emails'].get('processed', 0)} emails")


def example_step_by_step():
    """Step-by-step execution."""
    print("\n=== STEP-BY-STEP EXECUTION ===\n")
    
    agent = ZeroInboxAgent()
    
    # Step 1: Initialize
    print("Step 1: Initialize system")
    agent.setup()
    print("   ✅ System ready")
    
    # Step 2: Check LLM providers
    print("\nStep 2: Check LLM providers")
    llm_status = agent.get_llm_status()
    for provider, status in llm_status.items():
        icon = "✅" if status['api_key_found'] and status['package_available'] else "❌"
        print(f"   {icon} {provider.upper()}")
    
    # Step 3: Process some emails
    print("\nStep 3: Process a few emails")
    result = agent.categorize_emails(batch_size=3, limit=3)
    print(f"   Processed: {result['processed']} emails")
    
    # Step 4: Export if we have results
    if result['processed'] > 0:
        print("\nStep 4: Export results")
        export_result = agent.export_results()
        print(f"   Exported to: {export_result['export_path']}")


def example_minimal_categorization():
    """Minimal categorization example - just the essentials."""
    print("\n=== MINIMAL CATEGORIZATION ===\n")
    
    agent = ZeroInboxAgent()
    
    # Just categorize 5 emails - no output
    result = agent.run(
        ['setup', 'categorize_emails'],
        categorize_emails={'batch_size': 5}
    )
    
    processed = result['categorize_emails']['processed']
    print(f"Processed {processed} emails")
    
    # Show sample results if any
    if result['categorize_emails']['results']:
        print("\nSample categorizations:")
        for i, res in enumerate(result['categorize_emails']['results'][:2], 1):
            print(f"  {i}. {res['category']}/{res['subcategory']} (confidence: {res['confidence']:.2f})")


if __name__ == "__main__":
    # Run examples
    try:
        example_basic_usage()
        example_custom_parameters() 
        example_step_by_step()
        example_minimal_categorization()
        
        print("\n🎉 All examples completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")