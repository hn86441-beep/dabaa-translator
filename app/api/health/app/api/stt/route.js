import { NextResponse } from "next/server";

export async function POST(request) {
  try {
    const body = await request.json();
    
    // ضع كود الترجمة الحقيقي هنا
    const result = "تم استلام الطلب بنجاح من السيرفر";
    
    return NextResponse.json({ 
      success: true, 
      message: "تمت المعالجة بنجاح", 
      result: result 
    });
  } catch (error) {
    return NextResponse.json({ error: "حدث خطأ في السيرفر" }, { status: 500 });
  }
}
