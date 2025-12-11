"""
Setup and verification script for Gosling2
"""
import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible"""
    print("Checking Python version...")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True


def install_dependencies():
    """Install required dependencies"""
    print("\nInstalling dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Production dependencies installed")

        # Try to install dev dependencies
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements-dev.txt"])
            print("✓ Development dependencies installed")
        except subprocess.CalledProcessError:
            print("⚠ Could not install development dependencies (optional)")

        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def verify_structure():
    """Verify project structure"""
    print("\nVerifying project structure...")

    required_dirs = [
        "src",
        "src/data",
        "src/data/models",
        "src/data/repositories",
        "src/business",
        "src/business/services",
        "src/presentation",
        "src/presentation/views",
        "src/presentation/widgets",
        "src/resources",
        "tests",
        "tests/unit",
        "tests/integration",
    ]

    required_files = [
        "app.py",
        "requirements.txt",
        "README.md",
        "pyproject.toml",
    ]

    all_ok = True

    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists() and path.is_dir():
            print(f"✓ {dir_path}/")
        else:
            print(f"❌ Missing directory: {dir_path}/")
            all_ok = False

    for file_path in required_files:
        path = Path(file_path)
        if path.exists() and path.is_file():
            print(f"✓ {file_path}")
        else:
            print(f"❌ Missing file: {file_path}")
            all_ok = False

    return all_ok


def run_tests():
    """Run test suite"""
    print("\nRunning tests...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-v"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✓ All tests passed")
            return True
        else:
            print("⚠ Some tests failed")
            print(result.stdout)
            print(result.stderr)
            return False
    except Exception as e:
        print(f"⚠ Could not run tests: {e}")
        return False


def main():
    """Main setup function"""
    print("=" * 60)
    print("Gosling2 Setup and Verification")
    print("=" * 60)

    # Check Python version
    if not check_python_version():
        sys.exit(1)

    # Verify structure
    if not verify_structure():
        print("\n❌ Project structure verification failed")
        sys.exit(1)

    # Install dependencies
    if not install_dependencies():
        print("\n❌ Dependency installation failed")
        sys.exit(1)

    # Run tests
    run_tests()

    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print("\nTo run the application:")
    print("  python app.py")
    print("\nTo run tests:")
    print("  pytest")
    print("\nTo run tests with coverage:")
    print("  pytest --cov=src tests/")
    print("=" * 60)


if __name__ == "__main__":
    main()

