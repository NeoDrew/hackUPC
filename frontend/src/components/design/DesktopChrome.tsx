"use client";

import { usePathname } from "next/navigation";

/** Hides children on /m routes (phone-immersive). Used twice in the root
 * layout: once around TopBar+TabBar, once around the page-padded <main>. */
export function DesktopChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (pathname.startsWith("/m")) return null;
  return <>{children}</>;
}

/** Inverse: renders children only on /m routes. */
export function PhoneOnly({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (!pathname.startsWith("/m")) return null;
  return <>{children}</>;
}
