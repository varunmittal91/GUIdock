#!/usr/bin/env python2

from json import load
from urlparse import urlparse

import logging

def add_to_dependency(src, dependencies):
    from os import path,walk
    if path.isfile(src):
        dependencies.append(src)
    else:
        append = dependencies.append
        for root,dirs,files in walk(src):
            [append("%s/%s" % (root,file)) for file in files]

def process_add(command, arg, dep, lib_path, dependencies):
    src,dst = arg.split()
    urlparts = urlparse(src)
    if not urlparts.scheme or urlparts.scheme == 'file':
        src = "%s/%s" % (lib_path,urlparts.path)
        arg = "%s %s" % (src,dst)
        import os.path
        add_to_dependency(src, dependencies)
    return command,arg

command_dict = {
    "repo_update": ["RUN apt-get -y update --allow-unauthenticated", None],
    "repo_add"   : ["RUN add-apt-repository -y", lambda command,arg,dep,lib_path,dependencies: (command,"'%s'" % arg)],
    "install"    : ["RUN apt-get install -y --force-yes --no-install-recommends", None],
    "purge"      : ["RUN apt-get purge -y --force-yes", None],
    "add"        : ["add", process_add],
    "copy"       : ["copy", process_add]
}

def load_dep(dep, commands=[], expose_ports=[], entry_points=[], scripts=[], env=[], workdir=[], contributors=[], maintainers=[],
                 add_repos=[], install_packages=[], purge_packages=[], dependencies=[], installed_dependencies=[]):
    # Check if dependency already installed
    if dep in installed_dependencies:
        return
    installed_dependencies.append(dep)

    # Check if the dependency is git repository, by default assumed to be local plugin in ./lib
    type = "local"
    lib_path = None
    try:
        type,repo = dep.split('/', 1)
        # Path to sync repo
        repo_path = "repos/%s" % repo
        repo_url  = "http://github.com/%s" % repo

        # Capture output of git clone
        from subprocess import call
        command = ["git", "clone", repo_url, repo_path]
        status  = 0
        status  = call(command)
        if status == 128:
            logging.debug("# Assuming directory was already created by previous sync, attempting to pull the latest changes")
        command = ["git", "--work-tree", repo_path, "pull"]
        status = call(command)
        if status != 0:
            print("Failed to import git repo: %s" % repo_url)
            exit(1)
        path = "%s/dep.json" % repo_path
        lib_path = repo_path
    except ValueError:
        path = "lib/%s.json" % dep
        lib_path = "lib/%s" % dep

    try:
        json_data = load(open(path, "rb"))
    except Exception as e:
        from sys import exit
        print("Failed to import %s: %s" % (dep, e))
        exit(1)
    depends = json_data.get('depends', [])
    commands.append("#%s.json" % dep)
    for _dep in depends:
        load_dep(_dep, commands, scripts=scripts, env=env, install_packages=install_packages, purge_packages=purge_packages, 
                     add_repos=add_repos, entry_points=entry_points, expose_ports=expose_ports, dependencies=dependencies, 
                     installed_dependencies=installed_dependencies)
    for command in json_data['commands']:
        try:
            command,arg = command
        except ValueError:
            arg = ""
        if command == "install":
            install_packages.extend(arg.split())
        elif command == "purge":
            purge_packages.extend(arg.split())
        else:
            # Save for matching special commands that are not to be added global list
            orig_command = command
            command,fnc = command_dict.get(command, ["RUN %s" % command, None])
            if fnc:
                command,arg = fnc(command,arg,dep,lib_path,dependencies)
            command = "%s %s" % (command, arg)
            if orig_command == "repo_add":
                add_repos.append(command)
            else:
                commands.append(command)
    commands.append("#--")

    expose = json_data.get('expose', [])
    expose_ports.extend(expose)

    for _env in json_data.get("env", []):
        env.append(_env)

    entry_point = json_data.get("entrypoint", [])
    if entry_point:
        entry_points.append(entry_point)
    try:
        script,script_opts = json_data.get("script")
    except ValueError:
        script = json_data.get("script")
        script_opts = {'remove': True}
    except TypeError:
        script = None
    if script:
        from uuid import uuid4
        # Generate uuid4 name for first time setup script
        file_name = str(uuid4())
        arg = "%s /%s" % (script,file_name)
        command,arg = process_add("add", arg, dep, lib_path, dependencies)
        command = "%s %s" % (command,arg)
        commands.append(command)
        command_str = "/%s" % file_name
        scripts.append("chmod +x %s" % command_str)
        scripts.append("/bin/bash %s \$@" % command_str)
        if script_opts['remove']:
            scripts.append("rm -rf %s" % command_str)
    workdir = workdir + json_data.get('workdir', [])
    contributors = contributors+json_data.get('maintainer', [])

    return commands,expose_ports,entry_points,scripts,env,workdir,contributors

def load_json(json_path, dockerfile=None, zippath=None):
    import json
    data = load(open(json_path, "rb"))
    maintainer = data.get('maintainer')
    if maintainer:
        maintainer = "MAINTAINER %s" % maintainer
    base_image = "FROM ubuntu:14.04"
    if not dockerfile:
        dockerfile = [
            maintainer,
            "ENV DEBIAN_FRONTEND noninteractive",
            "ENV HOME /root",
            "RUN apt-get update",
            "RUN apt-get install -y --force-yes --no-install-recommends software-properties-common apt-transport-https",
        ]

    # Collect local variables from all components and create a central list of commands
    sub_commands = []
    expose_ports = []
    entry_points = []
    scripts      = []
    env          = []
    workdir      = []
    maintainers  = []
    add_repos    = []
    install_packages = []
    purge_packages   = []
    dependencies = []
    installed_dependencies = []
    for lib in data.get('libs', []):
        load_dep(lib, expose_ports=expose_ports, entry_points=entry_points, scripts=scripts, env=env, workdir=workdir,
                     maintainers=maintainers, add_repos=add_repos, commands=sub_commands,
                     install_packages=install_packages, purge_packages=purge_packages, dependencies=dependencies, 
                     installed_dependencies=installed_dependencies)

    # aggregate repo additions
    dockerfile.extend(add_repos)
    dockerfile.append(command_dict['repo_update'][0])

    # aggregate install commands
    command,fnc = command_dict['install']
    dockerfile.append("%s %s" % (command," ".join(install_packages)))

    for maintainer in set(maintainers):
        dockerfile = ["MAINTAINER %s" % maintainer]+dockerfile

    dockerfile.extend(sub_commands)

    # aggregate purge commands
    if purge_packages:
        command,fnc = command_dict['purge']
        dockerfile.append("%s %s" % (command," ".join(purge_packages)))

    dockerfile.extend([
        "RUN apt-get purge software-properties-common -y --force-yes",
        "RUN apt-get -y autoclean",
        "RUN apt-get -y autoremove",
        "RUN rm -rf /var/lib/apt/lists/*",
        "RUN rm -rf /tmp/*",
        "RUN rm -rf /var/tmp/*"
    ])

    for _env in env:
        dockerfile.append("ENV %s" % _env)
    # Honour last workdir
    if workdir:
        dockerfile.append("WORKDIR %s" % workdir[-1])

    # Add expose ports to final Dockerfile
    if expose_ports:
        dockerfile.append("EXPOSE %s" % " ".join(expose_ports))

    if entry_points:
        entry_point = "%s %s" % (" ".join(entry_points[-1]), "\$@")
        scripts.append(entry_point)
    exec_command = 'echo -e "%s" >> /entrypoint.sh' % ("\\n".join(["#!/bin/bash"]+scripts))
    dockerfile.append("RUN bash -c '%s'" % exec_command)
    dockerfile.append("RUN chmod +x /entrypoint.sh")
    dockerfile.append("ENTRYPOINT %s" % json.dumps(["/entrypoint.sh"]))
    
    dockerfile = "\n".join([base_image]+dockerfile)
    # Check dependencies and create a zip archive for shipping linked files
    if zippath:
        import zipfile
        zipf = zipfile.ZipFile(zippath, 'w', zipfile.ZIP_DEFLATED)
        [zipf.write(dependency) for dependency in dependencies]
        zipf.writestr("Dockerfile", dockerfile)

    return dockerfile

if __name__=="__main__":
    from sys import argv
    from getopt import getopt

    json_file = None
    outputfile = None
    zippath    = None

    opts,args = getopt(argv[1:], "f:o:z:", ["file=", "outputfile=", "zip="])
    for opt,arg in opts:
        if opt in ['-f', '--file']:
            json_file = arg
        elif opt in ['-o', '--outputfile']:
            outputfile = arg
        elif opt in ['-z', '--zip']:
            zippath = arg
    if not json_file:
        print "Input file needed, -f, --file"
        exit(1)
    out_json_file = load_json(json_file, zippath=zippath)
    if outputfile:
        out_file = open(outputfile, "wb")
        out_file.write(out_json_file)
    else:
        print out_json_file
