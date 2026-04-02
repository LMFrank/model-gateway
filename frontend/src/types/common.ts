export type JsonPrimitive = string | number | boolean | null

export type JsonValue = JsonPrimitive | JsonObject | JsonValue[]

export interface JsonObject {
  [key: string]: JsonValue
}

export interface ApiListResponse<T> {
  items: T[]
}

export interface ApiCreatedResponse<T> {
  id: number
  item: T
}

export interface ApiItemResponse<T> {
  item: T
}

export interface ApiMessageResponse {
  message: string
}
