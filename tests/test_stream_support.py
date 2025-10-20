"""Test script for stream functionality.

This script validates that:
1. Stream handler can parse IDs correctly
2. Channel mapping works as expected
3. Stream objects are generated properly
4. Environment variables are loaded correctly
"""
import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from stream_handler import stream_handler, parse_stream_id
from channel_streams import get_stream_url, get_available_channels, is_channel_supported
from models import StremioStream


async def test_parse_stream_id():
    """Test stream ID parsing."""
    print("\n=== Testing Stream ID Parsing ===")
    
    test_cases = [
        ("musortv:amc-hd:1760943000:rendorsztori", True),
        ("musortv:rtl:1234567890:matrix", True),
        ("invalid:format", False),
        ("musortv:channel", False),
        ("tt0032138", False),
    ]
    
    for test_id, should_pass in test_cases:
        result = parse_stream_id(test_id)
        status = "✅ PASS" if (result is not None) == should_pass else "❌ FAIL"
        print(f"{status}: {test_id} -> {result}")


async def test_channel_mapping():
    """Test channel stream URL mapping."""
    print("\n=== Testing Channel Mapping ===")
    
    # Show available channels
    available = get_available_channels()
    print(f"\nConfigured channels ({len(available)}):")
    for channel in available:
        url = get_stream_url(channel)
        print(f"  ✓ {channel}: {url[:50]}..." if url else f"  ✗ {channel}: (no URL)")
    
    if not available:
        print("  ⚠️  No channels configured! Set STREAM_* environment variables.")
    
    # Test some common channels
    print("\nTesting common channel names:")
    test_channels = ["RTL", "TV2", "AMC HD", "HBO", "M1"]
    for channel_name in test_channels:
        supported = is_channel_supported(channel_name)
        url = get_stream_url(channel_name)
        status = "✅" if supported else "❌"
        print(f"  {status} {channel_name}: {'Supported' if supported else 'Not configured'}")


async def test_stream_handler():
    """Test stream handler with various inputs."""
    print("\n=== Testing Stream Handler ===")
    
    test_cases = [
        ("movie", "musortv:amc-hd:1760943000:rendorsztori", "Valid musortv ID"),
        ("movie", "musortv:rtl:1234567890:test", "Valid RTL stream"),
        ("movie", "tt0032138", "IMDb ID (should fail)"),
        ("series", "musortv:rtl:123:test", "Wrong type"),
    ]
    
    for type_, id_, description in test_cases:
        print(f"\nTest: {description}")
        print(f"  Input: {type_}/{id_}")
        
        result = await stream_handler(type_, id_)
        streams = result.get("streams", [])
        
        if streams:
            print(f"  ✅ Got {len(streams)} stream(s)")
            for i, stream in enumerate(streams, 1):
                print(f"    Stream {i}:")
                print(f"      Name: {stream.get('name')}")
                print(f"      URL: {stream.get('url', '')[:60]}...")
        else:
            print(f"  ℹ️  No streams (expected if channel not configured)")


async def test_stream_model():
    """Test StremioStream model."""
    print("\n=== Testing StremioStream Model ===")
    
    try:
        stream = StremioStream(
            url="https://example.com/test.m3u8",
            name="🔴 TEST CHANNEL",
            title="Test Stream",
            description="Test description",
            behaviorHints={"notWebReady": False}
        )
        
        print("✅ Model created successfully")
        print(f"  Model dict: {stream.model_dump()}")
        
    except Exception as e:
        print(f"❌ Model creation failed: {e}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Stream Functionality Test Suite")
    print("=" * 60)
    
    # Show environment info
    print("\n=== Environment Configuration ===")
    stream_vars = {k: v for k, v in os.environ.items() if k.startswith("STREAM_")}
    print(f"Found {len(stream_vars)} STREAM_* environment variables")
    
    if stream_vars:
        print("\nConfigured streams:")
        for key, value in sorted(stream_vars.items()):
            if value:
                print(f"  ✓ {key}: {value[:50]}...")
            else:
                print(f"  ✗ {key}: (empty)")
    else:
        print("  ⚠️  No STREAM_* variables set!")
        print("  Set environment variables like: STREAM_RTL=https://example.com/rtl.m3u8")
    
    # Run tests
    await test_parse_stream_id()
    await test_channel_mapping()
    await test_stream_model()
    await test_stream_handler()
    
    print("\n" + "=" * 60)
    print("Testing Complete!")
    print("=" * 60)
    
    # Summary
    available = get_available_channels()
    if available:
        print(f"\n✅ {len(available)} channel(s) configured and ready to stream")
    else:
        print("\n⚠️  No channels configured. Add STREAM_* environment variables to enable streaming.")
        print("\nExample:")
        print("  export STREAM_RTL=https://your-iptv-provider.com/rtl.m3u8")
        print("  export STREAM_TV2=https://your-iptv-provider.com/tv2.m3u8")


if __name__ == "__main__":
    asyncio.run(main())
