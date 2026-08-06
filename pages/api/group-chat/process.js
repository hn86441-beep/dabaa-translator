export default function handler(req, res) {
  if (req.method === 'POST') {
    return res.status(200).json({ success: true, message: "تمت معالجة الدردشة" });
  }
  res.status(405).json({ error: "Method Not Allowed" });
}
