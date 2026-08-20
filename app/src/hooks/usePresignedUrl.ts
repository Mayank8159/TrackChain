// Request and cache presigned S3 URLs for media playback.

import { useState, useEffect } from "react";
import { api } from "../lib/api";

export function usePresignedUrl(filename?: string, contentType = "video/mp4") {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!filename) {
      setUrl(null);
      return;
    }

    let isMounted = true;
    setLoading(true);

    api
      .getPresignedUploadUrl(filename, contentType)
      .then((res) => {
        if (isMounted) {
          setUrl(res.fileUrl);
          setError(null);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message);
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [filename, contentType]);

  return { url, loading, error };
}
