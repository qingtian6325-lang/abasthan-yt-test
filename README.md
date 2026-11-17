# abasthan-yt-test

Minimal test app for Abasthan: checks whether yt-dlp on Abasthan's
servers can extract a YouTube stream URL (datacenter IP block check).

- `GET /` — health + yt-dlp version
- `GET /yt-test` — extraction test for a fixed public video, returns JSON.
  Optional `?url=<youtube watch url>` to test another video.

Metadata extraction test only. No video is downloaded, proxied or streamed.
