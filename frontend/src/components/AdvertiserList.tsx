import { api } from "@/lib/api";
import { SidebarLink } from "./SidebarLink";

export async function AdvertiserList() {
  const advertisers = await api.listAdvertisers();
  return (
    <ul>
      {advertisers.map((a) => (
        <li key={a.advertiser_id}>
          <SidebarLink href={`/advertisers/${a.advertiser_id}`}>
            {a.advertiser_name} <small>({a.vertical})</small>
          </SidebarLink>
        </li>
      ))}
    </ul>
  );
}
