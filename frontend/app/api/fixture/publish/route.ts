import { NextResponse } from "next/server";
import { FixtureError, fixturePublish } from "@/lib/fixtureState";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    // Deliberate delay so the pending UI state is actually visible while
    // building against fixtures. Real publishing is slower than this.
    await new Promise((resolve) => setTimeout(resolve, 700));
    return NextResponse.json(fixturePublish(String(body.selection_id ?? "")));
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
