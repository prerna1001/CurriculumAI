import { NextResponse } from "next/server";
import { FixtureError, fixtureSearch } from "@/lib/fixtureState";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const subject = typeof body.subject === "string" ? body.subject.trim() : "";
    const level = typeof body.level === "string" ? body.level.trim() : "";

    if (!subject) {
      return NextResponse.json(
        { error: { code: "invalid_input", message: "subject must be a non-empty string.", retryable: false } },
        { status: 422 },
      );
    }

    return NextResponse.json(fixtureSearch(subject, level || "undergraduate"));
  } catch (err) {
    if (err instanceof FixtureError) {
      return NextResponse.json(
        { error: { code: err.code, message: err.message, retryable: err.retryable } },
        { status: err.status },
      );
    }
    throw err;
  }
}
