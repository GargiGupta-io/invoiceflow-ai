resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${local.name_prefix}-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name_prefix}-igw" }
}

resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  availability_zone       = local.azs[count.index]
  cidr_block              = var.public_subnet_cidrs[count.index]
  map_public_ip_on_launch = false

  tags = { Name = "${local.name_prefix}-public-${count.index + 1}" }
}

resource "aws_subnet" "app" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  availability_zone       = local.azs[count.index]
  cidr_block              = var.app_subnet_cidrs[count.index]
  map_public_ip_on_launch = false

  tags = { Name = "${local.name_prefix}-app-${count.index + 1}" }
}

resource "aws_subnet" "database" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  availability_zone       = local.azs[count.index]
  cidr_block              = var.database_subnet_cidrs[count.index]
  map_public_ip_on_launch = false

  tags = { Name = "${local.name_prefix}-db-${count.index + 1}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name_prefix}-public" }
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "public" {
  count = 2

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_eip" "nat" {
  count = local.nat_gateway_count

  domain = "vpc"
  tags   = { Name = "${local.name_prefix}-nat-${count.index + 1}" }

  depends_on = [aws_internet_gateway.main]
}

resource "aws_nat_gateway" "main" {
  count = local.nat_gateway_count

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  tags          = { Name = "${local.name_prefix}-nat-${count.index + 1}" }

  depends_on = [aws_internet_gateway.main]
}

resource "aws_route_table" "app" {
  count = 2

  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name_prefix}-app-${count.index + 1}" }
}

resource "aws_route" "app_egress" {
  count = local.is_showcase ? 0 : 2

  route_table_id         = aws_route_table.app[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id = aws_nat_gateway.main[
    var.single_nat_gateway ? 0 : count.index
  ].id
}

resource "aws_route_table_association" "app" {
  count = 2

  subnet_id      = aws_subnet.app[count.index].id
  route_table_id = aws_route_table.app[count.index].id
}

resource "aws_route_table" "database" {
  count = 2

  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name_prefix}-db-${count.index + 1}" }
}

resource "aws_route_table_association" "database" {
  count = 2

  subnet_id      = aws_subnet.database[count.index].id
  route_table_id = aws_route_table.database[count.index].id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = local.runtime_s3_route_tables

  tags = { Name = "${local.name_prefix}-s3" }
}
