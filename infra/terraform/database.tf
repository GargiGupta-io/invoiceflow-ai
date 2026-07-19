resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-database"
  subnet_ids = aws_subnet.database[*].id

  tags = { Name = "${local.name_prefix}-database" }
}

resource "aws_db_instance" "main" {
  identifier = "${local.name_prefix}-postgres"

  engine                      = "postgres"
  engine_version              = "16"
  instance_class              = var.database_instance_class
  db_name                     = var.database_name
  username                    = var.database_username
  manage_master_user_password = true

  allocated_storage     = var.database_allocated_storage
  max_allocated_storage = var.database_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  multi_az               = var.database_multi_az
  publicly_accessible    = false
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.database.id]
  port                   = 5432

  backup_retention_period   = 7
  copy_tags_to_snapshot     = true
  deletion_protection       = var.database_deletion_protection
  skip_final_snapshot       = var.database_skip_final_snapshot
  final_snapshot_identifier = var.database_skip_final_snapshot ? null : "${local.name_prefix}-final"

  auto_minor_version_upgrade   = true
  apply_immediately            = false
  performance_insights_enabled = true

  tags = { Name = "${local.name_prefix}-postgres" }
}
