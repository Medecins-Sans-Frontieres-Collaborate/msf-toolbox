#!/usr/bin/env python3
"""
Validate that setuptools_scm version matches the Git tag.

This script is used in the GitHub Actions publish workflow to ensure
the package version matches the release tag.

Usage:
    python scripts/validate_version.py <scm_version> <git_tag>
    
Exit codes:
    0: Version validation passed
    1: Version mismatch or error
"""

import sys
from packaging.version import parse, Version


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/validate_version.py <scm_version> <git_tag>")
        sys.exit(1)
    
    scm_version = sys.argv[1]
    tag_version = sys.argv[2]
    
    print(f"SCM Version: {scm_version}")
    print(f"Git Tag: {tag_version}")
    
    try:
        # Parse the versions
        scm_parsed = parse(scm_version)
        tag_parsed = parse(tag_version)
        
        # Extract base version (without local/dev/post parts)
        scm_base = scm_parsed.base_version
        tag_base = tag_parsed.base_version
        
        print(f"SCM base version: {scm_base}")
        print(f"Tag base version: {tag_base}")
        
        # For releases, we expect the base versions to match
        if scm_base != tag_base:
            print(f"ERROR: Base version mismatch: setuptools_scm={scm_base}, tag={tag_base}")
            sys.exit(1)
        
        # Additional check: for a release tag, setuptools_scm should give us a clean version
        # when running on the exact tag commit. Different suffixes indicate different scenarios:
        #
        # - is_devrelease (e.g., 1.2.3.dev4): A development version indicating 4 commits
        #   since the base version (1.2.3) was tagged. This typically happens during
        #   development between releases.
        #
        # - post is not None (e.g., 1.2.3.post1): A post-release version, usually indicates
        #   commits after a release tag. Similar to dev but follows PEP 440 post-release format.
        #
        # - local is not None (e.g., 1.2.3+g1234567): Contains local version identifiers,
        #   often includes git commit hash. Indicates the working directory has additional commits.
        #
        # For a proper release, none of these should be present - we expect a clean version
        # that exactly matches the tag (e.g., "1.2.3"). However, we treat these as warnings
        # rather than errors because the build might still be valid (e.g., for test builds).
        if scm_parsed.is_devrelease or scm_parsed.post is not None or scm_parsed.local is not None:
            print(f"WARNING: setuptools_scm returned a non-release version: {scm_version}")
            print("This may indicate the tag is not on the current commit.")
            print("Expected a clean version matching the tag for a release build.")
            # We'll allow this to proceed but log the warning
        
        print("Version validation passed!")
        return 0
        
    except Exception as e:
        print(f"ERROR: Failed to parse versions: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())