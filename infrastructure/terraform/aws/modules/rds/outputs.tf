output "endpoint" {
  description = "RDS instance endpoint (host:port)"
  value       = aws_db_instance.main.endpoint
}

output "address" {
  description = "RDS instance hostname"
  value       = aws_db_instance.main.address
}

output "port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "database_name" {
  description = "Name of the default database"
  value       = aws_db_instance.main.db_name
}

output "instance_id" {
  description = "ID of the RDS instance"
  value       = aws_db_instance.main.id
}

output "security_group_id" {
  description = "Security group ID for the RDS instance"
  value       = aws_security_group.rds.id
}
