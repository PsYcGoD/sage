    # Test MCP config
    config_path = Path(__file__).parent.parent / "sage-mcp.json"
    try:
        with open(config_path) as f:
            config = json.load(f)
        print(f"\n[OK] MCP config file exists")
        print(f"  Server name: {config['name']}")
        print(f"  Tools: {len(config['tools'])}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"\n[SKIP] MCP config issue: {e}")
