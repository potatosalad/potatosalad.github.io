#!/usr/bin/env ruby

Jekyll::Hooks.register :site, :post_write do |site|
  script = File.expand_path("../util/highlight-starry-night.mjs", __dir__)
  success = system("node", script, site.dest)
  next if success

  raise Jekyll::Errors::FatalException, "Starry Night post-processing failed"
end
