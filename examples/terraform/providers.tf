# TerraGuard example infrastructure — scanned statically (no apply, no backend).
# This is a demonstration baseline: mostly secure, with a few intentional
# minor gaps so the posture score is realistic (not a perfect 100).

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
  # No credentials configured — TerraGuard performs static analysis only.
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "demo"
}
