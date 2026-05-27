# IAM — scoped role for the app instance. No wildcards, no AdministratorAccess.

resource "aws_iam_role" "app" {
  name = "terraguard-demo-app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "app_s3_read" {
  name = "terraguard-demo-app-s3-read"
  role = aws_iam_role.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:ListBucket"
      ]
      Resource = [
        aws_s3_bucket.assets.arn,
        "${aws_s3_bucket.assets.arn}/*"
      ]
    }]
  })
}

resource "aws_iam_instance_profile" "app" {
  name = "terraguard-demo-app-profile"
  role = aws_iam_role.app.name
}
