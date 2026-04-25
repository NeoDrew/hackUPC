import type { Metadata } from "next";
import { Inter, Roboto_Mono } from "next/font/google";

import "./globals.css";
import "./advisor.css";

import { ChatLauncher } from "@/components/design/ChatLauncher";
import { DesktopChrome, PhoneOnly } from "@/components/design/DesktopChrome";
import { TopBar } from "@/components/design/TopBar";
import {
  getActiveAdvertiser,
  listAdvertisersForPicker,
} from "@/lib/advertiserScope";
import { getActiveWeek, getDatasetBounds } from "@/lib/periodScope";

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
  title: "Smadex Cooking",
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
  const [active, advertisers, bounds, activeWeek] = await Promise.all([
    getActiveAdvertiser(),
    listAdvertisersForPicker(),
    getDatasetBounds(),
    getActiveWeek(),
  ]);
  return (
    <html lang="en" className={`${inter.variable} ${robotoMono.variable}`}>
      <body>
        <DesktopChrome>
          <TopBar
            advertisers={advertisers}
            activeAdvertiserId={active?.advertiser_id ?? null}
            totalWeeks={bounds.total_weeks}
            activeWeek={activeWeek}
          />
          <main className="page-pad">{children}</main>
        </DesktopChrome>
        <PhoneOnly>{children}</PhoneOnly>
        <ChatLauncher />
      </body>
    </html>
  );
}
