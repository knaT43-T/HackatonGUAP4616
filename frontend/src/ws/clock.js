// Оценка смещения часов клиента относительно сервера.
//
// Сервер в каждом pong возвращает свой server_time и эхо нашего client_time.
// Кандитат смещения: server_time - (client_time + rtt / 2) — считаем, что
// сетевая задержка делится пополам между запросом и ответом.
// Берём замер с минимальным RTT: у него меньше погрешность. Держим скользящее
// окно, чтобы старые измерения не жили вечно (см. API.md §7, front.md §11).

const WINDOW_SIZE = 8;
const MAX_RTT_MS = 10_000;

export function createClock() {
  const samples = [];

  function register(clientTime, serverTime) {
    if (!Number.isFinite(clientTime) || !Number.isFinite(serverTime)) return;
    const rtt = Date.now() - clientTime;
    if (rtt < 0 || rtt > MAX_RTT_MS) return;

    samples.push({ rtt, offset: serverTime - (clientTime + rtt / 2) });
    if (samples.length > WINDOW_SIZE) samples.shift();
  }

  function best() {
    let result = null;
    for (const sample of samples) {
      if (result === null || sample.rtt < result.rtt) result = sample;
    }
    return result;
  }

  return {
    register,
    get offsetMs() {
      const sample = best();
      return sample ? sample.offset : 0;
    },
    get rttMs() {
      const sample = best();
      return sample ? sample.rtt : null;
    },
  };
}
