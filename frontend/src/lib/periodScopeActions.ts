"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";

import { WEEK_COOKIE } from "@/lib/periodScope";

const COOKIE_MAX_AGE = 60 * 60 * 24 * 30;

export async function setActiveWeek(formData: FormData) {
  const raw = formData.get("week");
  const store = await cookies();
  if (raw === null || raw === "") {
    store.delete(WEEK_COOKIE);
    revalidatePath("/", "layout");
    return;
  }
  const n = typeof raw === "string" ? Number.parseInt(raw, 10) : NaN;
  if (!Number.isFinite(n) || n <= 0) {
    store.delete(WEEK_COOKIE);
    revalidatePath("/", "layout");
    return;
  }
  store.set(WEEK_COOKIE, String(n), {
    path: "/",
    maxAge: COOKIE_MAX_AGE,
    sameSite: "lax",
  });
  revalidatePath("/", "layout");
}
