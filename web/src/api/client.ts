/**
 * The typed HTTP client.
 *
 * `schema.gen.ts` is generated from the server's OpenAPI document
 * (`npm run gen`), so every path, parameter and body below is checked against
 * what the API actually accepts — a renamed property is a compile error here,
 * not a surprise at runtime.
 */

import createClient from "openapi-fetch";
import type { components, paths } from "./schema.gen";

export type Schemas = components["schemas"];

export type Profile = Schemas["ProfileOut"];
export type Month = Schemas["MonthOut"];
export type MonthSummary = Schemas["MonthSummaryOut"];
export type Section = Schemas["SectionOut"];
export type Field = Schemas["FieldOut"];
export type Income = Schemas["IncomeOut"];
export type Pocket = Schemas["PocketOut"];
export type Transaction = Schemas["TransactionOut"];
export type Transfer = Schemas["TransferOut"];
export type FieldRef = Schemas["FieldRef"];
export type Change = Schemas["ChangeOut"];
export type ClosePreview = Schemas["ClosePreviewOut"];
export type SectionKind = Schemas["SectionKind"];
export type RestRouting = Schemas["RestRoutingModel"];
export type AmountOrPercent = Schemas["AmountOrPercent"];

/** Same origin: the dev server and nginx both forward /api to the backend. */
export const api = createClient<paths>();

/** A refused request, in the API's one error shape (`ErrorOut`). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  /** The input at fault, when the server could tell — forms mark that field. */
  readonly field: string | null;

  constructor(status: number, code: string, message: string, field: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.field = field;
  }

  /** The month changed under us (HTTP 412): what we hold is out of date. */
  get stale(): boolean {
    return this.status === 412;
  }
}

interface Result<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

/** Resolve to the response body, or throw an `ApiError`. */
export async function unwrap<T>(request: Promise<Result<T>>): Promise<T> {
  let result: Result<T>;
  try {
    result = await request;
  } catch {
    throw new ApiError(
      0,
      "network",
      "Can't reach the Monay server. Check that it is running, then try again.",
    );
  }
  if (!result.response.ok) throw toApiError(result.error, result.response.status);
  return result.data as T;
}

function toApiError(body: unknown, status: number): ApiError {
  if (typeof body === "object" && body !== null && "message" in body) {
    const { code, message, field } = body as Partial<Schemas["ErrorOut"]>;
    if (typeof message === "string") {
      return new ApiError(status, code ?? "error", message, field ?? null);
    }
  }
  // Not one of ours: a proxy's error page, or the server is down behind it.
  return new ApiError(status, "error", `The server answered with an error (${status}).`);
}
