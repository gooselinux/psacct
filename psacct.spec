# Our /usr/bin/last is in the SysVInit packae
%define with_last     0

%define FHS_compliant 1

%if %{FHS_compliant}
%define accounting_logdir       /var/account
%else
%define accounting_logdir       /var/log
%endif

Summary: Utilities for monitoring process activities
Name: psacct
Version: 6.3.2
Release: 63%{?dist}
# alloca.c and part of common.c has Public Domain license
License: GPLv2+ and Public Domain
Group: Applications/System
Source: ftp://ftp.gnu.org/pub/gnu/acct/acct-%{version}.tar.gz
Source1: psacct.init
# This dumb patch breaks FHS 2.2 compliance, so it is disabled now except
# in 7.x builds.  Do not use it in new products.
Patch0: acct-6.3.2-config.patch
Patch1: acct-6.3.2-exit.patch
# Fixes some broken calls to ctime() on 64bit arch's <mharris@redhat.com>
Patch2: psacct-6.3.2-64bit-fixes.patch
Patch3: psacct-6.3.2-hzval-fixes2.patch
Patch4: acct-6.3.2-pts.patch
Patch5: psacct-6.3.2-strictmatch.patch
Patch6: psacct-6.3.2-sa-manfix.patch
Patch7: psacct-6.3.2-LargeFile.patch
Patch8: psacct-6.3.2-lastcomm_man.patch
Patch9: acct-6.3.2-sa_manpage.patch
# fix the psacct to deal with all acct types
# if it is possible and wanted then add the possibility
# to display the pid and ppid number
Patch10: psacct-6.3.2-ppid.patch
Patch11: psacct-6.3.2-man-pages.patch

Buildroot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Requires: /sbin/chkconfig /sbin/install-info
BuildRequires: autoconf
Requires: coreutils

# This conflict is to avoid psacct being forced on by old initscripts now that
# we have a proper initscript in place. initscripts 6.55 and later are fixed.
Conflicts: initscripts < 6.55

%description
The psacct package contains several utilities for monitoring process
activities, including ac, lastcomm, accton and sa. The ac command
displays statistics about how long users have been logged on. The
lastcomm command displays information about previous executed
commands. The accton command turns process accounting on or off. The
sa command summarizes information about previously executed
commands.

%prep
%setup -q -n acct-%{version}

%if ! %{FHS_compliant}
%patch0 -p0 -b .config
%endif
%patch1 -p1 -b .psacct-exit
%patch2 -p0 -b .64bit-fixes
%patch3 -p1 -b .hz
%patch4 -p1 -b .pts
%patch5 -p1 -b .strictmatch
%patch6 -p1 -b .tio-avio
%patch7 -p1 -b .lfs
%patch8 -p1 -b .man
%patch9 -p1 -b .pct
%patch10 -p1 -b .acct
%patch11 -p1 -b .new

%build
%if ! %{FHS_compliant}
autoconf
%endif

%configure
sed -e "s/\/\* #undef HAVE_LINUX_ACCT_H \*\//#define HAVE_LINUX_ACCT_H/" config.h > config.h.new
sed -e "s;#define HAVE_ACIO 1;/* #undef HAVE_ACIO */;" config.h.new > config.h
touch texinfo.tex
make

%install
[ "$RPM_BUILD_ROOT" != "/" ] && rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT{/sbin,%{_bindir},%{_mandir},%{_sbindir}}
make install prefix=$RPM_BUILD_ROOT%{_prefix} \
        bindir=$RPM_BUILD_ROOT%{_bindir} sbindir=$RPM_BUILD_ROOT%{_sbindir} \
        infodir=$RPM_BUILD_ROOT%{_datadir}/info mandir=$RPM_BUILD_ROOT%{_mandir}
cp dump-acct.8 dump-utmp.8 $RPM_BUILD_ROOT%{_mandir}/man8/

# move accton to /sbin -- leave historical symlink
mv $RPM_BUILD_ROOT%{_sbindir}/accton $RPM_BUILD_ROOT/sbin/accton
ln -s ../../sbin/accton $RPM_BUILD_ROOT%{_sbindir}/accton

# remove unwanted file
rm -f $RPM_BUILD_ROOT%{_infodir}/dir

gzip -9f $RPM_BUILD_ROOT%{_infodir}/*
mkdir -p $RPM_BUILD_ROOT%{accounting_logdir}
touch $RPM_BUILD_ROOT%{accounting_logdir}/pacct

# Create logrotate config file
mkdir -p $RPM_BUILD_ROOT/etc/logrotate.d
cat > $RPM_BUILD_ROOT/etc/logrotate.d/psacct <<EOF
# Logrotate file for psacct RPM
 
%{accounting_logdir}/pacct {
#prerotate loses accounting records, let's no
#   prerotate
#       %{_sbindir}/accton
#   endscript
    compress
    delaycompress
    notifempty
    daily
    rotate 31
    create 0600 root root
    postrotate
       %{_sbindir}/accton %{accounting_logdir}/pacct
    endscript
}     
EOF

# Install initscript
mkdir -p $RPM_BUILD_ROOT/etc/rc.d/init.d
install -m 755 %{SOURCE1} $RPM_BUILD_ROOT/etc/rc.d/init.d/psacct

%if ! %{with_last}
rm -f $RPM_BUILD_ROOT%{_bindir}/last $RPM_BUILD_ROOT%{_mandir}/man1/last.1*
%endif

%clean
[ "$RPM_BUILD_ROOT" != "/" ] && rm -rf $RPM_BUILD_ROOT

%post
/sbin/chkconfig --add psacct
# we need this hack to get rid of an old, incorrect accounting info entry.
if [ $1 = 0 ]; then
  test -f /etc/info-dir && {
    grep -v '* accounting: (psacct)' < /etc/info-dir > /etc/info-dir.new
    mv -f /etc/info-dir.new /etc/info-dir
  }
  /sbin/install-info %{_infodir}/accounting.info.gz %{_infodir}/dir --entry="* accounting: (accounting).            The GNU Process Accounting Suite."
fi
touch %{accounting_logdir}/pacct

%preun
if [ $1 = 0 ]; then
  /sbin/install-info --delete %{_infodir}/accounting.info.gz %{_infodir}/dir --entry="* accounting: (accounting).            The GNU Process Accounting Suite." 2>/dev/null
  /sbin/service psacct stop > /dev/null 2>&1
  /sbin/chkconfig --del psacct
fi

%files
%doc README COPYING
%defattr(-,root,root,-)
%if %{FHS_compliant}
%dir /var/account
%endif
/etc/rc.d/init.d/psacct
%attr(0600,root,root)   %ghost %config %{accounting_logdir}/pacct
%attr(0644,root,root)   %config(noreplace) /etc/logrotate.d/*
/sbin/accton
%{_sbindir}/accton
%{_sbindir}/sa
%{_sbindir}/dump-utmp
%{_sbindir}/dump-acct
%{_bindir}/ac
%if %{with_last}
%{_bindir}/last
%endif
%{_bindir}/lastcomm
%{_mandir}/man1/ac.1*
%if %{with_last}
%{_mandir}/man1/last.1*
%endif
%{_mandir}/man1/lastcomm.1*
%{_mandir}/man8/sa.8*
%{_mandir}/man8/accton.8*
%{_mandir}/man8/dump-acct.8*
%{_mandir}/man8/dump-utmp.8*
%{_infodir}/accounting.info.gz

%changelog
* Mon Apr 19 2010 Ivana Hutarova Varekova <varekova@redhat.com> - 6.2.3-63
- Related: # 575762
  fix the initscript output

* Mon Apr 19 2010 Ivana Hutarova Varekova <varekova@redhat.com> - 6.2.3-62
- Resolves: # 575762
  fix initscript

* Mon Feb 22 2010 Ivana Hutarova Varekova <varekova@redhat.com> - 6.3.2-61
- Resolves: #543948
  minor spec file changes

* Mon Dec 21 2009 Ivana Hutarova Varekova <varekova@redhat.com> - 6.3.2-60
- Resolves: #548731
  fix license and source tag

* Tue Dec  8 2009 Ivana Hutarova Varekova <varekova@redhat.com> - 6.3.2-59
- fix the initscript (service restart does not work)

* Wed Dec  2 2009 Ivana Hutarova Varekova <varekova@redhat.com> - 6.3.2-58
- add dump-utmp.8 and dump-acct.8 man-pages

* Fri Nov 26 2009 Ivana Varekova <varekova@redhat.com> - 6.3.2-57
- fix the ac_version variable handle on ppc64 (BIG_ENDIAN machine)

* Fri Nov 13 2009 Ivana Varekova <varekova@redhat.com> - 6.3.2-56
- fix the psacct to deal with all acct types and
  if it is possible and wanted then add the possibility
  to display the pid and ppid number

* Wed Sep 16 2009 Ivana Varekova <varekova@redhat.com> - 6.3.2-55
- fix init script (#521195)

* Sun Jul 26 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 6.3.2-54
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Thu Feb 26 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 6.3.2-53
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Tue Nov 13 2008 Ivana Varekova <varekova@redhat.com> - 6.3.2-52
- remove link to nonexisting page from sa man-page

* Tue Jun  3 2008 Ivana Varekova <varekova@redhat.com> - 6.3.2-51
- remove unwanted file

* Wed Feb 20 2008 Fedora Release Engineering <rel-eng@fedoraproject.org> - 6.3.2-50
- Autorebuild for GCC 4.3

* Fri Jan 18 2008 Ivana Varekova <varekova@redhat.com> - 6.3.2-49
- rebuilt

* Tue Aug 28 2007 Fedora Release Engineering <rel-eng at fedoraproject dot org> - 6.3.2-48
- Rebuild for selinux ppc32 issue.

* Wed Jul 25 2007 Ivana Varekova <varekova@redhat.com> - 6.3.2-47
- fix status service

* Wed Jul 25 2007 Ivana Varekova <varekova@redhat.com> - 6.3.2-46
- Resolves: #247034
  fix init script

* Mon May 28 2007 Ivana Varekova <varekova@redhat.com> - 6.3.2-45
- fix the return value of "service psacct status" command

* Thu Apr  5 2007 Ivana Varekova <varekova@redhat.com> - 6.3.2-44
- small spec changes
- change buildroot
- remove makeinstall macro

* Tue Jan 23 2007 Ivana Varekova <varekova@redhat.com> - 6.3.2-43
- Resolves: 223728
  psacct logrotate file looks for non existant directory

* Tue Jan  2 2007 Ivana Varekova <varekova@redhat.com> - 6.3.2-42
- Resolves: 221069
  (fix lastcomm man page)
- spec file cleanup

* Wed Jul 12 2006 Jesse Keating <jkeating@redhat.com> - 6.3.2-41.1
- rebuild

* Mon Feb 27 2006 Peter Jones <pjones@redhat.com> - 6.3.2-41
- add touch to prereq

* Mon Feb 27 2006 Ivana Varekova <varekova@redhat.com> - 6.3.2-40
- add chkconfig to prereq - bug 182848

* Mon Feb 20 2006 Ivana Varekova <varekova@redhat.com> - 6.3.2-39
- add Large File Support 

* Fri Feb 10 2006 Jesse Keating <jkeating@redhat.com> - 6.3.2-38.2
- bump again for double-long bug on ppc(64)

* Tue Feb 07 2006 Jesse Keating <jkeating@redhat.com> - 6.3.2-38.1
- rebuilt for new gcc4.1 snapshot and glibc changes

* Tue Jan  3 2006 Ivana Varekova <varekova@redhat.com> 6.3.2-38
- fix typo bug 176811

* Fri Dec 09 2005 Jesse Keating <jkeating@redhat.com>
- rebuilt

* Fri Mar  4 2005 Ivana Varekova <varekova@redhat.com> 6.3.2-37
- rebuilt

* Tue Feb 15 2005 Ivana Varekova <varekova@redhat.com> 6.3.2-36
- fix sa manpage - necessary becouse of bug #43294 and previous patch

* Tue Feb 15 2005 Ivana Varekova <varekova@redhat.com> 6.3.2-35
- fix #147782 logrotate script error

* Thu Feb  3 2005 Charles Bennett <ccb@redhat.com> 6.3.2-33.fc4
- rhbz 133077: logrotate fixed to continue accounting during rotate
- rhbz 141802: lastcomm was not handling all forms of --strict-match
- rhbz 141971: rpm -e no longer leaves /var/lock/subsys/psacct
- rhbz 43294: sa will never report any io because the kernel doesn't
   provide it.  Tweaked to ignore ac_io in acct.h
- integrate lastcomm hz patch from RH support

* Wed Sep  1 2004 root <ccb@redhat.com> - 6.3.2-31
- integrate JFenlason's hz patch, improve pts device reporting

* Fri Feb 13 2004 Elliot Lee <sopwith@redhat.com>
- rebuilt

* Wed Jun 04 2003 Elliot Lee <sopwith@redhat.com>
- rebuilt

* Wed Jan 22 2003 Tim Powers <timp@redhat.com>
- rebuilt

* Thu Dec 26 2002 Florian La Roche <Florian.LaRoche@redhat.de>
- make /etc/info-dir an optional file

* Wed Nov 13 2002 Mike A. Harris <mharris@redhat.com> 6.3.2-25
- Added with_last conditional to disable /usr/bin/last because ours is in
  the SysVInit package.  This fixes unpackaged files terminate build prob.

* Thu Aug 22 2002 Mike A. Harris <mharris@redhat.com> 6.3.2-24
- Fixed initscript reload/restart by creating start/stop functions and
  making everything use them (#72261)

* Tue Aug  6 2002 Mike A. Harris <mharris@redhat.com> 6.3.2-23
- Fixed chkconfig issue in rpm scripts (#61191)
- Excludearch ia64, not taking the time to debug/troubleshoot random
  buildsystem failure due to higher priorities.

* Mon Jul 08 2002 Elliot Lee <sopwith@redhat.com>
- Take the time to make sure things get through on all archs, by simply
  running it through the build system.

* Fri Jun 21 2002 Tim Powers <timp@redhat.com>
- automated rebuild

* Thu May 23 2002 Tim Powers <timp@redhat.com>
- automated rebuild

* Tue Mar 27 2002 Mike A. Harris <mharris@redhat.com> 6.3.2-19
- Made initscript touch/chmod accounting file if it is not present during
  startup, to ensure accounting works properly when enabled.

* Mon Mar 26 2002 Mike A. Harris <mharris@redhat.com> 6.3.2-18
- Fixed duh in initscript pointing to wrong accounting file (#61939)

* Sun Mar 17 2002 Mike A. Harris <mharris@redhat.com> 6.3.2-17
- Removed the files usracct and savacct, which are not used by psacct
  utilities at all, but by the sa program.  Our sa uses files in a different
  location, and so these files are unused and unnecessary.

* Sat Mar 16 2002 Mike A. Harris <mharris@redhat.com> 6.3.2-16
- Added chkconfig to post and preun scripts for bug (#61191)

* Tue Mar 12 2002 Mike A. Harris <mharris@redhat.com> 6.3.2-15
- Added new feature - psacct initscript now controls process accounting so
  that it is not just forced on if installed as was the previous behaviour
- Modified the initscripts package to not force psacct on anymore and made
  the new psacct-6.3.2-15 conflict with previous initscripts packages.
- Fixed logrotate config to set perms/owner of new log files, and closed
  bug (#54165)

* Thu Mar  7 2002 Mike A. Harris <mharris@redhat.com> 6.3.2-14
- Fixed 64bit bug in calls to ctime() in lastcomm and dump-utmp (#60712)

* Wed Mar  6 2002 Mike A. Harris <mharris@redhat.com> 6.3.2-13
- Removed Build_7x flag, added FHS_compliant flag, reworked specfile to use new
  flag, and fixed bug (#60716)

* Thu Feb 28 2002 Bill Nottingham <notting@redhat.com> 6.3.2-12
- rebuild in new environment for FHS correctness

* Thu Jan 31 2002 Mike A. Harris <mharris@redhat.com> 6.3.2-11
- Conditionalized acct-6.3.2-config.patch to only be applied for RHL 7.x
  builds, as it breaks FHS compliance by putting files in nonstandard
  locations.  Also fixed up other places in specfile for FHS 2.2.
- Added acct-6.3.2-I-HATE-GNU-AUTOCONK.patch because I hate GNU autoconk
  really really badly.
  
- Bumped to -11 to avoid buildsystem stupidness

* Thu Sep 06 2001 Mike A. Harris <mharris@redhat.com> 6.3.2-9
- Fixed bug (#53307) psacct is enabled by default, and the log files
  are huge, and will fill the disk up very quickly.  logrotate will
  now compress them daily.

* Sat Sep 01 2001 Florian La Roche <Florian.LaRoche@redhat.de> 6.3.2-8
- do not fail for ENOSYS to silently support kernels without
  process accounting

* Sun Aug 26 2001 Mike A. Harris <mharris@redhat.com> 6.3.2-7
- Change spec tag Copyright -> License
- change logrotate to rotate daily, and keep 1 month (31 days) of data

* Sun Jun 24 2001 Elliot Lee <sopwith@redhat.com>
- Bump release + rebuild.

* Mon Feb 02 2001 Helge Deller <hdeller@redhat.de>
- added logrotate file for /var/log/pacct (#24900)

* Wed Jul 12 2000 Prospector <bugzilla@redhat.com>
- automatic rebuild

* Mon Jun  5 2000 Nalin Dahyabhai <nalin@redhat.com>
- FHS fixes

* Sat May  6 2000 Bill Nottingham <notting@redhat.com>
- fix for new patch

* Thu Feb 03 2000 Nalin Dahyabhai <nalin@redhat.com>
- update to 6.3.2

* Mon Apr 05 1999 Preston Brown <pbrown@redhat.com>
- wrap post script with reference count.

* Tue Mar 23 1999 Preston Brown <pbrown@redhat.com>
- install-info sucks.  Still.

* Sun Mar 21 1999 Cristian Gafton <gafton@redhat.com> 
- auto rebuild in the new build environment (release 8)

* Thu Mar 18 1999 Bill Nottingham <notting@redhat.com>
- #define HAVE_LINUX_ACCT_H too, so it works. :)

* Sun Aug 16 1998 Jeff Johnson <jbj@redhat.com>
- accton needs to be accessible to /etc/rc.d/init.d/halt

* Fri May 08 1998 Erik Troan <ewt@redhat.com>
- install-info sucks

* Mon Apr 27 1998 Prospector System <bugs@redhat.com>
- translations modified for de, fr, tr

* Thu Oct 23 1997 Donnie Barnes <djb@redhat.com>
- updated from 6.2 to 6.3

* Mon Jul 21 1997 Erik Troan <ewt@redhat.com>
- built against glibc
