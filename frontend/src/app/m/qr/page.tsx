import { headers } from "next/headers";
import QRCode from "qrcode";

export const dynamic = "force-dynamic";

export default async function QrLandingPage(props: {
  searchParams: Promise<{ to?: string }>;
}) {
  const { to } = await props.searchParams;
  const phoneUrl = await resolvePhoneUrl(to);
  const svg = await QRCode.toString(phoneUrl, {
    type: "svg",
    margin: 1,
    width: 280,
    color: { dark: "#0d0a14", light: "#ffffff" },
  });
  return (
    <main className="qr-landing">
      <section className="qr-landing-card">
        <h1>Scan to follow on your phone</h1>
        <p>
          Open your camera, point at the code, and the Smadex Twin Copilot
          opens in immersive mobile mode. Swipe up through the deck while we
          walk you through the data.
        </p>
        <div
          className="qr-frame"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
        <span className="qr-url">{phoneUrl}</span>
      </section>
    </main>
  );
}

async function resolvePhoneUrl(override: string | undefined): Promise<string> {
  if (override) return override;
  // Production override: judges scan a stable URL.
  const explicit = process.env.NEXT_PUBLIC_PHONE_URL;
  if (explicit) return explicit;
  // Local fallback: build from incoming request headers.
  const h = await headers();
  const proto = h.get("x-forwarded-proto") ?? "http";
  const host = h.get("x-forwarded-host") ?? h.get("host") ?? "localhost:3001";
  return `${proto}://${host}/m`;
}
