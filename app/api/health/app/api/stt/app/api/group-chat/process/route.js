import { NextResponse } from "next/server";

export async function POST(request) {
  try {
    const body = await request.json();
    
    // ضع كود معالجة الدردشة هنا
    const result = "تمت معالجة الدردشة بنجاح";
    
    return NextResponse.json({ 
      success: true, 
      message: "تمت معالجة الدردشة", 
      result: result 
    });
  } catch (error) {
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
