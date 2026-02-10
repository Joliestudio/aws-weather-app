variable "aws_region" {
  description = "AWS 區域"
  default     = "ap-northeast-1" # 東京 (離台灣近且穩定)
}

variable "docker_image" {
  description = "Docker Hub 映像檔名稱 (例如: yourname/weather-app:latest)"
  type        = string
}

variable "weather_api_key" {
  description = "OpenWeatherMap API Key"
  type        = string
  sensitive   = true # 標記為敏感資料，避免直接顯示在 Log 中
}
variable "google_api_key" {
  description = "Google Gemini API Key"
  type        = string
  sensitive   = true
}