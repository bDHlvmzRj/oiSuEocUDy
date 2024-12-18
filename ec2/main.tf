# 各 workbook をループ処理
resource "aws_instance" "ec2" {
  for_each = { for workbook, sheets in var.workbooks : workbook => sheets }

  # workbook 内の各シートをループ
  dynamic "sheets" {
    for_each = each.value

    content {
      ami           = sheets.value.aws_instance.ami
      instance_type = sheets.value.aws_instance.instance_type

      tags = {
        Name = "ec2-${each.key}-${sheets.key}"
      }
    }
  }
}
