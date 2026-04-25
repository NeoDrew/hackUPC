import { api } from "@/lib/api";
import { CampaignList } from "@/components/CampaignList";

export default async function AdvertiserPage(
  props: PageProps<"/debug/advertisers/[advertiserId]">,
) {
  const { advertiserId } = await props.params;
  const id = Number(advertiserId);
  const advertiser = await api.getAdvertiser(id);
  return (
    <section>
      <h2>
        {advertiser.advertiser_name} <small>({advertiser.vertical} · HQ {advertiser.hq_region})</small>
      </h2>
      <CampaignList advertiserId={id} />
    </section>
  );
}
