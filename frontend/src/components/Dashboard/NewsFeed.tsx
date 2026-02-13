import { useEffect, useState } from "react";
import { Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { fetchNews } from "../../services/api";

type NewsItem = {
  headline: string;
  source: string;
  timestamp: string;
  symbols: string[];
  sentiment: string;
};

const NewsFeed = () => {
  const [items, setItems] = useState<NewsItem[]>([]);

  useEffect(() => {
    fetchNews()
      .then((data) => setItems(data?.items || []))
      .catch(() => setItems([]));
  }, []);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          News & Sentiment
        </Typography>
        <Stack spacing={2}>
          {items.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              No news available.
            </Typography>
          )}
          {items.map((item, idx) => (
            <Stack key={`${item.headline}-${idx}`} spacing={1}>
              <Typography variant="subtitle2">{item.headline}</Typography>
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography variant="caption" color="text.secondary">
                  {item.source} · {new Date(item.timestamp).toLocaleTimeString()}
                </Typography>
                <Chip label={item.sentiment} size="small" />
                {item.symbols.map((symbol) => (
                  <Chip key={symbol} label={symbol} size="small" variant="outlined" />
                ))}
              </Stack>
            </Stack>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default NewsFeed;
