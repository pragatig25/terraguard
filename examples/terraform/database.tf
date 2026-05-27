# Database — RDS encrypted at rest, private, Multi-AZ.

resource "aws_db_instance" "app" {
  identifier     = "terraguard-demo-db"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.micro"

  allocated_storage = 20
  storage_encrypted = true # CIS 2.3.1

  username = "dbadmin"
  # Password is supplied at apply time via a secret manager reference,
  # never hardcoded here.
  manage_master_user_password = true

  publicly_accessible = false # CIS 2.3.3
  multi_az            = true  # CIS 2.3.2

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  backup_retention_period = 7
  skip_final_snapshot     = false
  final_snapshot_identifier = "terraguard-demo-db-final"

  tags = {
    Name        = "terraguard-demo-db"
    Environment = var.environment
  }
}
