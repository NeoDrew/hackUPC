import type { Metadata } from "next";
import { Inter, Roboto_Mono } from "next/font/google";

import "./globals.css";

import { DesktopChrome, PhoneOnly } from "@/components/design/DesktopChrome";
import { TopBar } from "@/components/design/TopBar";
import { TabBar } from "@/components/design/TabBar";
import { api } from "@/lib/api";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  weight: ["400", "500", "600", "700"],
});

const robotoMono = Roboto_Mono({
  subsets: ["latin"],
  variable: "--font-roboto-mono",
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Smadex Creative Twin Copilot",
  description: "Creative intelligence cockpit for mobile advertising",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover" as const,
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const counts = await api.tabCounts();
  return (
    <html lang="en" className={`${inter.variable} ${robotoMono.variable}`}>
      <body>
        <DesktopChrome>
          <TopBar />
          <TabBar counts={counts} />
          <main className="page-pad">{children}</main>
        </DesktopChrome>
        <PhoneOnly>{children}</PhoneOnly>
      </body>
    </html>
  );
}
