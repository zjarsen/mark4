#!/usr/bin/env python3
"""
Test script to verify all imports work correctly.
This tests the new architecture without starting the bot.
"""

import sys
import traceback

def test_import(module_name, description):
    """Test importing a module."""
    try:
        print(f"Testing {description}...", end=" ")
        __import__(module_name)
        print("✅ OK")
        return True
    except Exception as e:
        print(f"❌ FAILED")
        print(f"  Error: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all import tests."""
    print("=" * 60)
    print("Import Test Suite - New Architecture")
    print("=" * 60)

    tests = [
        # Configuration
        ("config", "Configuration"),

        # Database Layer
        ("database", "Database package"),
        ("database.exceptions", "Database exceptions"),
        ("database.models", "Database models"),
        ("database.connection", "Database connection"),
        ("database.repositories", "Repositories package"),
        ("database.repositories.user_repo", "User repository"),
        ("database.repositories.transaction_repo", "Transaction repository"),
        ("database.repositories.payment_repo", "Payment repository"),
        ("database.migrations", "Migrations package"),

        # Domain Layer
        ("domain", "Domain package"),
        ("domain.credits", "Credits package"),
        ("domain.credits.service", "Credit service"),
        ("domain.credits.discount", "Discount service"),
        ("domain.workflows", "Workflows package"),
        ("domain.workflows.base", "Base workflow"),
        ("domain.workflows.image", "Image workflow package"),
        ("domain.workflows.image.service", "Image workflow service"),
        ("domain.workflows.image.processors", "Image processors"),
        ("domain.workflows.video", "Video workflow package"),
        ("domain.workflows.video.service", "Video workflow service"),
        ("domain.workflows.video.processors", "Video processors"),

        # Infrastructure Layer
        ("infrastructure", "Infrastructure package"),
        ("infrastructure.state", "State package"),
        ("infrastructure.state.manager", "State manager"),
        ("infrastructure.state.redis_impl", "Redis state manager"),
        ("infrastructure.state.memory_impl", "In-memory state manager"),
        ("infrastructure.comfyui", "ComfyUI package"),
        ("infrastructure.comfyui.exceptions", "ComfyUI exceptions"),
        ("infrastructure.comfyui.client", "ComfyUI client"),
        ("infrastructure.notifications", "Notifications package"),
        ("infrastructure.notifications.service", "Notification service"),
        ("infrastructure.files", "Files package"),
        ("infrastructure.files.service", "File service"),

        # Core
        ("core.service_container", "Service container"),
        ("core.bot_application_v2", "Bot application v2"),
    ]

    results = []
    for module_name, description in tests:
        result = test_import(module_name, description)
        results.append((module_name, result))

    # Summary
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("✅ All imports successful!")
        return 0
    else:
        print("❌ Some imports failed")
        print("\nFailed imports:")
        for module_name, result in results:
            if not result:
                print(f"  - {module_name}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
