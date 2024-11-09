class GithubPrWatcher < Formula
  include Language::Python::Virtualenv

  desc "Desktop tool to monitor GitHub Pull Requests"
  homepage "https://github.com/gm2211/github-pr-watcher"
  version "1.0.0"
  
  url "https://github.com/gm2211/github-pr-watcher/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "0" # Will be updated on first release
  
  head do
    url "https://github.com/gm2211/github-pr-watcher.git", branch: "main"
  end
  
  depends_on "python@3.11"
  depends_on "poetry"

  def install
    venv = virtualenv_create(libexec, "python3.11")
    
    # Export dependencies to requirements.txt
    system Formula["poetry"].opt_bin/"poetry", "export", "--format", "requirements.txt", "--without-hashes", "--output", "requirements.txt"
    
    # Install dependencies
    venv.pip_install "-r", "requirements.txt"
    
    # Install source files
    prefix.install "src"
    prefix.install "pyproject.toml"
    prefix.install "poetry.lock"
    
    # Create launcher script
    (bin/"github-pr-watcher").write <<~EOS
      #!/bin/bash
      export PYTHONPATH="#{prefix}/src:#{libexec}/lib/python3.11/site-packages:$PYTHONPATH"
      exec "#{libexec}/bin/python3.11" -m src.main "$@"
    EOS
    chmod 0755, bin/"github-pr-watcher"
  end

  test do
    system bin/"github-pr-watcher", "--version"
  end
end
