import { NextResponse } from "next/server";

export async function POST(request) {
  try {
    const body = await request.json();
    
    // ضع كود معالجة الدردشة الجماعية الخاص بك هنا...
    
    return NextResponse.json({ success: true, message: "تمت معالجة الدردشة" });
  } catch (error) {
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
