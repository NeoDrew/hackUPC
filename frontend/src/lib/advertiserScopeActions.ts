"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";

import { ADVERTISER_COOKIE } from "@/lib/advertiserScope";

const COOKIE_MAX_AGE = 60 * 60 * 24 * 30;

export async function setActiveAdvertiser(formData: FormData) {
  const raw = formData.get("advertiser_id");
  const n = typeof raw === "string" ? Number.parseInt(raw, 10) : NaN;
  if (!Number.isFinite(n) || n <= 0) return;
  const store = await cookies();
  store.set(ADVERTISER_COOKIE, String(n), {
    path: "/",
    maxAge: COOKIE_MAX_AGE,
    sameSite: "lax",
  });
  revalidatePath("/", "layout");
}
