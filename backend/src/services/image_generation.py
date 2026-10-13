"""Image generation service using OpenAI GPT Image with S3 upload."""

import base64
import uuid
from datetime import datetime

import boto3

from src.core.database import settings
from src.core.logging import logger

GPT_IMAGE_MODEL = "gpt-image-1.5"


class ImageGenerationService:
    """Generates images via GPT Image and uploads them to S3."""

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
                model=GPT_IMAGE_MODEL,
                prompt=prompt,
                size="1024x1024",
                quality="auto",
                n=1,
            )
            image_b64 = response.data[0].b64_json
            if not image_b64:
                logger.warning("OpenAI returned empty image payload.")
                return None

            image_data = base64.b64decode(image_b64)

            if self.s3_client and self.s3_bucket:
                return self._upload_bytes_to_s3(image_data)

            # GPT Image models return base64 only; data URLs work for UI without S3.
            b64 = base64.b64encode(image_data).decode("ascii")
            return f"data:image/png;base64,{b64}"
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return None

    def _upload_bytes_to_s3(self, image_data: bytes) -> str | None:
        """Upload image bytes to S3 and return the public URL."""
        try:
            key = f"lifeos/images/{datetime.utcnow().isoformat()}_{uuid.uuid4()}.png"
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=image_data,
                ContentType="image/png",
            )

            url = f"https://{self.s3_bucket}.s3.{self.s3_region}.amazonaws.com/{key}"
            logger.info(f"Uploaded image to S3: {url}")
            return url
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return None


image_service = ImageGenerationService()
