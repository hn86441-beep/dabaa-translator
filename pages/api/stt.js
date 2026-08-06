export default function handler(req, res) {
  if (req.method === 'POST') {
    // ضع كود الترجمة هنا
    return res.status(200).json({ success: true, message: "تمت المعالجة" });
  }
  res.status(405).json({ error: "Method Not Allowed" });
}
