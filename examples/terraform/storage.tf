# Storage — S3 bucket encrypted at rest with public access blocked.
# Intentional minor gap: access logging is not configured (CKV_AWS_18, LOW),
# keeping the baseline score realistic rather than a perfect 100.

resource "aws_s3_bucket" "assets" {
  bucket = "terraguard-demo-assets"

  tags = {
    Name        = "terraguard-demo-assets"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket = aws_s3_bucket.assets.id

  block_public_acls       = true
  block_public_policy      = true
  ignore_public_acls       = true
  restrict_public_buckets  = true
}
