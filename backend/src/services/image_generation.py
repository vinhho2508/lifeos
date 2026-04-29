"""Image generation service using OpenAI DALL-E 3 with S3 upload."""

import uuid
from datetime import datetime

import boto3

from src.core.database import settings
from src.core.logging import logger


class ImageGenerationService:
    """Generates images via DALL-E 3 and uploads them to S3."""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.s3_bucket = getattr(settings, "S3_BUCKET_NAME", None)
        self.s3_region = getattr(settings, "AWS_REGION", "us-east-1")
        self.s3_client = None
        if self.s3_bucket:
            try:
                self.s3_client = boto3.client(
                    "s3",
                    region_name=self.s3_region,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize S3 client: {e}")

    async def generate_image(self, prompt: str) -> str | None:
        """Generate an image from a prompt and return its public URL.

        Returns the S3 URL of the uploaded image, or None if generation fails.
        """
        if not self.openai_api_key:
            logger.warning("No OPENAI_API_KEY set; skipping image generation.")
            return None

        try:
            import openai

            client = openai.AsyncOpenAI(api_key=self.openai_api_key)
            response = await client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
            if not image_url:
                logger.warning("OpenAI returned empty image URL.")
                return None

            # If S3 is configured, download and re-upload for persistence
            if self.s3_client and self.s3_bucket:
                return await self._upload_to_s3(image_url)

            # Otherwise return the temporary OpenAI URL (expires after ~1 hour)
            return image_url
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return None

    async def _upload_to_s3(self, image_url: str) -> str | None:
        """Download image from URL and upload to S3, return public URL."""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(image_url, timeout=60.0)
                resp.raise_for_status()
                image_data = resp.content

            key = (
                f"lifeos/images/{datetime.utcnow().isoformat()}_{uuid.uuid4()}.png"
            )
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=image_data,
                ContentType="image/png",
            )

            # Build URL (assumes bucket is public or has presigned access)
            url = (
                f"https://{self.s3_bucket}.s3.{self.s3_region}.amazonaws.com/{key}"
            )
            logger.info(f"Uploaded image to S3: {url}")
            return url
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            # Fallback to the original temporary URL
            return image_url


image_service = ImageGenerationService()
