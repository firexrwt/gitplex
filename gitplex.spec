Name:           gitplex
Version:        0.3.0
Release:        1%{?dist}
Summary:        Multi-repo git TUI on steroids

License:        MIT
URL:            https://github.com/firexrwt/gitplex
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros

Requires:       git
Requires:       python3-textual >= 0.47.0

%description
GitPlex is a terminal-based Git client built with Python and Textual.
Designed to replace GUI tools like GitHub Desktop while adding features
that are only practical in a terminal environment — primarily the ability
to manage and operate on many repositories simultaneously.

Key features:
- Multi-repo dashboard with real-time status
- Interactive staging with hunk mode
- Bulk pull/push/fetch across all repos concurrently
- Commit graph visualization
- Commit history actions (cherry-pick, revert, reset, amend)
- Branch management, stash, clone, remote management

%prep
%autosetup

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files gitplex

%files -f %{pyproject_files}
%license LICENSE
%doc README.md
%{_bindir}/gitplex

%changelog
* Tue Mar 03 2026 Stepan Eremeev <opensource@firexrwt.com> - 0.3.0-1
- Add CLI clone: gitplex <url> [--dest <path>]

* Mon Mar 02 2026 Stepan Eremeev <opensource@firexrwt.com> - 0.2.0-2
- Remove unused GitPython dependency (fixes install on Fedora 43)

* Sun Mar 01 2026 Stepan Eremeev <opensource@firexrwt.com> - 0.2.0-1
- Initial package
