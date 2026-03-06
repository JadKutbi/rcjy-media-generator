# GCP Solutions Developer - Agent Memory

## Veo 3.1 Video Extension API
- Extension uses `video=` parameter in `client.models.generate_videos()` from `google-genai` SDK
- Each extension adds 7 seconds to existing video
- Max 20 extensions = 148 seconds total
- Extension only supports 720p resolution
- The `video` parameter takes `operation.response.generated_videos[0].video` (the Video file object)
- API returns combined video (original + extensions) as a single file
- Prompt for extension: prepend "Continue the scene seamlessly." to maintain coherence
