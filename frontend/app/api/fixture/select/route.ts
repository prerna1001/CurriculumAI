import { NextResponse } from "next/server";
import { FixtureError, fixtureSelect } from "@/lib/fixtureState";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const sessionId = String(body.session_id ?? "");
    const cardIds = Array.isArray(body.card_ids) ? body.card_ids.map(String) : [];
    return NextResponse.json(fixtureSelect(sessionId, cardIds));
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
