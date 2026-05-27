# Logging — CloudTrail (multi-region, validated, KMS-encrypted) + VPC flow logs.

resource "aws_cloudtrail" "main" {
  name                          = "terraguard-demo-trail"
  s3_bucket_name                = aws_s3_bucket.assets.id
  is_multi_region_trail         = true # CIS 3.1
  enable_log_file_validation    = true # CIS 3.2
  include_global_service_events = true
  kms_key_id                    = aws_kms_key.logs.arn # CIS 3.8
}

resource "aws_kms_key" "logs" {
  description             = "KMS key for CloudTrail + flow logs"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_flow_log" "vpc" {
  vpc_id          = aws_vpc.main.id
  traffic_type    = "ALL" # CIS 5.2
  log_destination = aws_s3_bucket.assets.arn
  log_destination_type = "s3"
}
