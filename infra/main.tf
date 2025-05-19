provider "aws" {
  region = var.aws_region
}

# Placeholder resources
resource "aws_s3_bucket" "civicforge_logs" {
  bucket = "civicforge-logs-${var.environment}"
}
