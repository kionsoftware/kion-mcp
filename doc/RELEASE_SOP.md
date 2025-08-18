Release SOP
===========

1. Run scripts/version_bump.py
2. Create section in `CHANGELOG.md` that matches the new version
    - Write release paragraph at the top of the new release section in changelog
    - Ensure all non-backend, non-administrative PR's are accounted for in subsections (changed, added, etc)
    - Stub out new placeholder for next release at top of changelog
3. Push and merge into main
4. Checkout main locally, pull from upstream
5. Tag with the release version and push
    ```bash
    git tag -a v0.1.0 -m "Release v0.1.0"
    git push origin v0.1.0
    ```
6. Monitor release pipeline and ensure it passes