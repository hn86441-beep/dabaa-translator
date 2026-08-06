export async function GET(request) {
  return new Response(JSON.stringify({ status: "ok", message: "Server is healthy" }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
