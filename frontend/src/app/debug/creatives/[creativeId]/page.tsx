import { api } from "@/lib/api";
import { CreativeDetail } from "@/components/CreativeDetail";
import { TimeseriesChart } from "@/components/TimeseriesChart";

export default async function CreativePage(
  props: PageProps<"/creatives/[creativeId]">,
) {
  const { creativeId } = await props.params;
  const id = Number(creativeId);
  const creative = await api.getCreative(id);
  return (
    <section>
      <CreativeDetail creative={creative} />
      <h3>Daily performance</h3>
      <TimeseriesChart creativeId={id} />
    </section>
  );
}
