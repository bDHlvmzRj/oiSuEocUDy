variable "workbooks" {
  description = "Mapping of workbook and sheet configurations"
  type = map(map(object({
    aws_instance = object({
      ami           = string
      instance_type = string
    })
  })))
}
