"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function SidebarLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const selected = pathname === href || pathname.startsWith(`${href}/`);
  return (
    <Link href={href} data-selected={selected ? "true" : undefined}>
      {children}
    </Link>
  );
}
