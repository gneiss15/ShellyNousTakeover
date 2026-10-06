Deutsche Version [hier](TODO.de.md).

# Open work

Version: 1.01

- [ ] Test the new NOUS takeover end to end on an unmodified device, including
  Rescue uploads and button Safe Boot. Historical migrations do not test this code.
- [ ] Test both MiniMain examples on hardware: startup, relay remaining OFF,
  web status and return to Rescue. Both builds and signatures have been checked.
- [ ] Verify the continuous stock-readiness check after an actual Shelly stock
  update. The added wait logic has been host-tested, not tested in a fresh migration.
- [ ] Extend hardware coverage for invalid Main images and unusable filesystems;
  distinguish host fault-injection results from physical device tests.
- [ ] Create separate TmrSwShelly and TmrSwA8T example repositories and add their links.
- [x] Check the final exported repository for private data, generated artifacts
  and applicable third-party notices before publication.

Current verification scope:
[hardware](HardwareTestResults.json), [host checks](HostTestResults.json),
[builds](BuildResults.json), [example builds](ExampleBuildResults.json) and
[source publication checks](PublicationCheckResults.json).
